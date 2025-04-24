

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Integer output_1 = Character.hashCode(input_1_0);
        Integer output_2 = Character.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 67 && output_2 == 68) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

