

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Integer output_1 = input_1_0.hashCode();
        Integer output_2 = input_2_0.hashCode();

        
        // Compare output
        if (output_1 == 69 && output_2 == 55) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

