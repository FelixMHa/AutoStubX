

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Integer output_1 = Character.getType(input_1_0);
        Integer output_2 = Character.getType(input_2_0);

        
        // Compare output
        if (output_1 == 26 && output_2 == 2) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

